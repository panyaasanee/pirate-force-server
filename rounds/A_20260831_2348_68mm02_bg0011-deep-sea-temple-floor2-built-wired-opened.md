# LANE-A round `68mm02`, 2026-08-31T23:48+07:00

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

บัญชี GM ที่ staged ไปฉาก 11 (Bg0011, Deep Sea Temple floor 2) หรือใช้ `/warp 11` แล้วล็อกอิน จะไม่โดน
ปฏิเสธที่หน้า login อีกต่อไป และจะเห็นตัวละคร/มอนสเตอร์ 51 ตัว (จาก 56 placement จริงของฉาก) ยืนอยู่ในวิหาร
ใต้น้ำ แทนที่จะเป็นฉากว่างเปล่าหรือการปฏิเสธล็อกอิน -- **ฉากนี้เป็นแถวความเสี่ยงสูง (`the_two_interiors`,
ร่วมกับฉาก 10 เท่านั้น)** จึงยังไม่ยืนยันว่าจุดเกิดยืนได้จริงหรือตกในหิน ต้องรอ GT-179 (attended)

## ลำดับประตูที่เลือกฉากนี้

ตาม COO-DECISION 20260830_1441 (สร้างสิบประตูที่สำรวจในรอบ `ga91m5` ตามลำดับ native placement count):
เปิดแล้ว 4(116), 5(92), 10(100), 14(81), 6(80), 8(76), 3(72), 7(68), 9(63) -- ตรวจสดจาก
`scenarios/world_scene_registry_001.json` ที่ working tree นี้ (หลัง merge PR #411 ของรอบ `ir0lpw`)
ยืนยัน `login_entry_allowed: true` ทั้งเก้าฉากนี้ตรงกับใบ 2312 ของรอบ `ir0lpw` เหลือปิดจากสิบประตูเดิมสอง
ฉาก: **11 (Bg0011, Deep Sea Temple floor 2, 56 placements) และ 130 (Bg4001, Navy Training Camp, 42
placements)** -- 11 มากกว่า เลือกฉากนี้

## สิ่งที่สร้าง (ฉาก 11 จริง)

- `src/pirateforce_foundation/world_bg0011_identity.py` (ใหม่) -- crosswalk ของ CLINE type 11: 26
  resolved / 5 unresolved จาก 31 Mob-Set numbers ที่ฉากใช้จริง (CLINE type 11 เต็มมี 32 คีย์ แต่ฉากนี้ใช้
  เพียง 31 -- คีย์ที่ไม่ใช้ (106) มี leader จริงแต่ก็จะ resolve ไม่ได้อยู่ดีเพราะ s_OUTFIT ว่างและชื่อเป็น
  CJK). ไม่มี "MOBS has no row" family (ต่างจากฉาก 9), มีแค่ family เดียว (no s_OUTFIT, 5 sets), มี 7
  sets multi-variant outfit (ทั้งหมด 2-variant), ครอบคลุม 27/51 shippable placements
- `src/pirateforce_foundation/world_population_bg0011.py` (ใหม่) -- census composer, 51/56 shippable
  placements, ไม่มี faction bit
- wiring จุดเดียวกับฉากก่อนหน้าทุกจุด: `world_scene_travel.CENSUS_SOURCES`,
  `world_population_handoff.ROSTER_COMPOSERS`, `lane_hooks/lane_a_scene_census.py` console reader,
  `mob_scene_recompose.ACKNOWLEDGED_WITHOUT_COMPOSER`
- `scenarios/world_scene_registry_001.json` แถว n_id=11: `login_entry_allowed: true` + safety-case
  narrative D1/D2/D3, ปรับ `why_the_ten_doors_are_shut` เป็น NINTH UPDATE (เหลือฉากปิดเดียว: 130)
  -- **ต่างจากฉากก่อนหน้าทั้งหมดตั้งแต่ฉาก 10: แถวนี้มี `table_row_differences.the_two_interiors`
  (elevated-risk flag)** ยึด precedent ของ COO-DECISION 20260831T10:42+07:00 (ยืนยันเปิดฉาก 10 บน flag
  เดียวกันโดยไม่ต้องรอ attended round ก่อน) ใช้ตัดสินใจเดียวกันกับฉากนี้โดยไม่ถามซ้ำ
- mechanical fallout ใน `tools/pf_runtimeres_actor_entry_static.py` (26→27, 35→36, 25→26) +
  `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` + `tests/test_runtimeres_actor_entry_static.py`
  -- ยืนยันตัวเลขด้วยการ grep ตรง (ไม่พึ่ง binary client ที่ไม่มีใน sandbox นี้): 27 actor-entry sites,
  36 stream sites, 26 modules ตรงกับที่ tool คำนวณเป๊ะ

## เทสที่เพิ่ม/แก้

- `tests/test_world_bg0011_identity.py`, `tests/test_world_population_bg0011.py` (ใหม่, 30 เทส/249
  subtests)
- `tests/test_lane_a_scene_census.py`: เพิ่ม `DeepSeaTempleFloor2RegistrationTests`
- ย้าย hardcode "ฉาก 11 = refused example" ไปฉาก 130 (Navy Training Camp, ฉากเดียวที่เหลือปิด): 6 ไฟล์
  (`test_gm_login_scene_admission.py`, `test_gm_login_scene_consume_cause.py`,
  `test_gm_login_scene_registry_snapshot.py`, `test_player_hostile_pairing.py`,
  `test_player_wire_probe_base1.py`, `test_world_faction_admission.py`)
- widen admissible-today lists ให้รวมฉาก 11 + เพิ่มเทส elevated-risk เฉพาะฉากนี้:
  `test_gm_login_scene_stage.py`, `test_gm_login_scene_sanctioned_barred.py`,
  `test_gm_login_scene_override_position_resync.py`, `test_world_scene_marker.py`
  (`test_scene_11_opened_separately_and_that_is_a_different_round`),
  `test_world_scene_registry_rule_1_scenes.py` (`test_the_ninth_scene_that_opened_is_no_longer_in_this_set`),
  `test_world_faction_admission.py`

## การตรวจสอบเข้มงวดด้วยตัวเอง (ไม่มี tool Agent เรียก pf-adversary ได้ในสภาพแวดล้อมนี้)

- Re-derive crosswalk ตรงจาก TSV จริงด้วยสคริปต์แยก (ไม่ใช่มือ): เช็ค CLINE type 11 = 32 rows, ไม่มี
  duplicate n_CREATURE_TYPE, scene ใช้ 31/32 คีย์, key 106 มี leader จริง (9061) แต่ MOBS row นั้น
  s_OUTFIT ว่างและชื่อเป็น CJK (ตรวจสองชั้นว่าจะ unresolved อยู่ดีแม้ถูกใช้)
- นับ shippable/unshippable ตรงจาก placements TSV: 51/5 ตรงกับที่ registry's native_placement_count (56)
  ลบ unresolved (5)
- ยืนยันระยะ marker-to-nearest-placement ที่คำนวณเอง (1107.764498...) ตรงกับตัวเลขที่ registry บันทึกไว้
  ก่อนหน้า (1107.764) เป๊ะ -- cross-check placement index 0 (Mob-Set 1) เป็นทั้งจุดที่ใกล้ที่สุดจริงและเป็น
  จุดที่ resolve ได้ (ไม่เหมือนฉาก 7 ที่จุดใกล้สุดดันไม่ resolve)
- ตรวจ cp874-encodability ของทุกไฟล์ใน src/ และ tools/ ด้วยสคริปต์แยก -- พบปัญหาหนึ่งจุด (ชื่อ CJK ของ MOBS
  row 9061 ที่เขียนลง docstring ตรงๆ) แก้แล้วโดยบรรยายแทนการ quote ตัวอักษรจริง แล้วตรวจซ้ำผ่าน
- รัน full test suite ของ server repo ซ้ำหลังแก้ทุกจุด: **5981 passed, 383 skipped, 13072 subtests
  passed, 0 failed** (เทียบกับ 5946/383/12751 ก่อนรอบนี้ -- เพิ่ม 35 tests/321 subtests, ไม่มี regression)
- ตรวจ `mob_scene_recompose.declared_without_composer()` คืนค่ารวมฉาก 11 แล้ว, `world_scene_travel.
  CENSUS_SOURCES`/`world_population_handoff.ROSTER_COMPOSERS` มี key `bg0011_roster` ครบทั้งสามจุด
- ไม่แตะ `runtime.py`, `app.py`, `current/pf_login_game_server_v141.py` เลย (grep ยืนยัน)

## ตัวเลขที่วัดได้

- assembled 51 shippable placements / 56 native placements (5 unshippable: ทั้งหมด no-s_OUTFIT family
  เดียว -- ต่างจากฉาก 9 ที่มีสองตระกูล)
- 26 resolved Mob-Set identities / 5 unresolved / 31 total ที่ฉากใช้จริง (CLINE type 11 มี 32 คีย์เต็ม แต่
  1 คีย์ไม่ถูกใช้: 106)
- 7 multi-variant outfit sets (ทั้งหมด 2-variant), ครอบคลุม 27 ของ 51 shippable placements
- discrepancy: native_definition_count ของ registry (31) ตรงกับจำนวนที่ฉากใช้จริงพอดี -- เหมือนฉาก 9
  (ครั้งที่สองที่ไม่ต่างกัน ต่างจากฉาก 3/4/6/7/8 ที่ต่าง ±1)
- full suite: 5981 passed, 383 skipped, 13072 subtests passed, 0 failed

## ยังไม่ได้พิสูจน์

- ไม่มีมนุษย์ยืนในฉากนี้มาก่อน จุดเกิด MARKER[11] ห่างจาก placement ที่ใกล้ที่สุด **1107.764 หน่วย** (อยู่ใน
  ขอบเขต placement) แต่ฉากนี้เป็น interior แบบ n_CANGLIDE=0/n_LIMIT_HEIGHT=0 และพื้น placement ต่ำสุดอยู่ที่
  z=-4592.9 ขณะที่ marker อยู่ z=380 (ต่างกันเกือบ 5000 หน่วย) -- **นี่คือแถวความเสี่ยงสูงตัวที่สองที่เลนนี้
  เปิด (คู่กับฉาก 10)** GT-179 เปิดแล้วใน pf_bridge/GAME_TEST_QUEUE.md เป็นแบบ dual-objective (มี
  actor ไหม + ยืนพื้นได้ไหม) ตามแม่แบบ GT-166
- ยังไม่ยืนยันว่า pf-adversary agent จริง (ไม่มี tool Agent ในสภาพแวดล้อมนี้) ตรวจซ้ำ -- ทำการตรวจสอบ
  ตัวเองอย่างเข้มงวดแทนตามหลักการเดียวกัน (ดูหัวข้อด้านบน) แต่ไม่ใช่การตรวจโดยบุคคล/agent ที่สอง

## ขอบเขตที่ไม่แตะ

`runtime.py`, `app.py`, `current/pf_login_game_server_v141.py` -- ไม่แตะเลย (grep ยืนยัน)

## CORE-REQUEST

ไม่มี

## เปิดใบให้สาย C

ไม่มี -- GT-179 ครอบคลุมแล้ว

-- LANE-A (WORLD) round `68mm02`
