# LANE-A round `78zayw`, 2026-08-31T21:52+07:00

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

บัญชี GM ที่ staged ไปฉาก 7 (Bg0007, Voodoo Island) หรือใช้ `/warp 7` แล้วล็อกอิน จะไม่โดนปฏิเสธที่หน้า
login อีกต่อไป และจะเห็นตัวละคร/มอนสเตอร์ 56 ตัว (จาก 68 placement จริงของฉาก) ยืนอยู่บนเกาะวูดู แทนที่จะเป็น
เกาะว่างเปล่าหรือการปฏิเสธล็อกอิน

## บริบท / ทำไมฉากนี้

ลำดับประตูที่ `COO-DECISION 2026-08-30T14:41+07:00` อนุมัติ (round `12lyda`'s placement-count table):
เปิดแล้ว 4(116), 5(92), 10(100), 14(81), 6(80), 8(76), 3(72, รอบ `p7wm17`). เหลือ 7(68), 9(63), 11(56),
130(42). **ฉาก 7 (Voodoo Island, 68 placements) เป็นตัวถัดไปที่มากที่สุดในสี่บานที่เหลือ** (68 > 63 ของฉาก
9) — ตามที่ CLAIM ของรอบนี้ระบุไว้ก่อนเริ่มงาน
(`pf_bridge/notes_to_chief/20260831_2128_CLAIM-LANE-A-round-78zayw-bg0007-voodoo-island.md`)

สร้าง+ผูก+เปิดในรอบเดียว ตามรูปแบบบีบอัดที่รอบ `l03cgh`/`fx0007`/`p4wire`/`p7wm17` ใช้กับฉาก 5/6/8/3:
เทสทั่วไป (`tests/test_lane_a_scene_census.py::ComposerContractTests`) สมมติไว้แล้วว่าทุกฉากที่ lane นี้
ผูก census ให้ต้องเปิดด้วย เพราะฉาก 3/4/5/6/8/10/14 เปิดหมดแล้วตอนรอบนี้เริ่ม

## สิ่งที่สร้าง

- `src/pirateforce_foundation/world_bg0007_identity.py` (ใหม่) — crosswalk ของ CLINE type 7:
  44 resolved / 12 unresolved จาก 56 Mob-Set numbers (CLINE type 7's ทั้งช่วง key, เหมือนฉาก 3/5/6/8)
  ไม่มี CJK-name drop (ทุก resolved identity เป็น ASCII) แต่มี 8 sets ที่ multi-variant outfit — ทุกตัว
  แค่สองตัวแปร (ต่างจากฉาก 3 ที่มีตัวหนึ่งเก้าตัวแปร)
- `src/pirateforce_foundation/world_population_bg0007.py` (ใหม่) — census composer, 56/68 shippable
  placements, ไม่มี faction bit (เป็นการตัดสินใจของสาย B), refuse ทุกฉากยกเว้น 7
- wiring: `world_scene_travel.py` (VOODOO_ISLAND_SCENE_ID=7 ใน CENSUS_SOURCES),
  `world_population_handoff.py` (ROSTER_COMPOSERS entry), `lane_hooks/lane_a_scene_census.py`
  (console reader), `mob_scene_recompose.py` (ACKNOWLEDGED_WITHOUT_COMPOSER entry — field_mobs
  ไม่รู้จักฉาก 7 เช่นกัน, co-maintenance edit บนไฟล์ของสาย B เหมือนที่รอบ p7wm17 ทำกับฉาก 3/4/5/6/8/10)
- `scenarios/world_scene_registry_001.json` แถว n_id=7: `login_entry_allowed: true` +
  `login_entry_allowed_because` (D1/D2/D3 safety case เหมือนฉาก 3/5/6/8), ปรับ narrative
  `why_the_ten_doors_are_shut` เป็น SEVENTH UPDATE (เหลือ 3 ฉากที่ยังปิด: 9, 11, 130)
- mechanical fallout ใน `tools/pf_runtimeres_actor_entry_static.py` (SRC_ACTOR_ENTRY_SITES
  24→25, SRC_ACTOR_STREAM_SITES 33→34, SRC_MODULES_WITH_ACTOR_ENTRY 23→24), re-pin ใน
  `tests/test_runtimeres_actor_entry_static.py` และในรายงาน
  `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md`

## เทสที่เพิ่ม/แก้

- `tests/test_world_bg0007_identity.py` (ใหม่), `tests/test_world_population_bg0007.py` (ใหม่)
- `tests/test_lane_a_scene_census.py`: เพิ่ม `VoodooIslandRegistrationTests`
- สิบไฟล์ admissible-scene-ids widened เป็นฉาก 7: `test_gm_login_scene_admission.py`,
  `test_gm_login_scene_override_position_resync.py`, `test_gm_login_scene_registry_snapshot.py`,
  `test_gm_login_scene_sanctioned_barred.py`, `test_gm_login_scene_stage.py`,
  `test_world_faction_admission.py`, `test_world_scene_marker.py`,
  `test_world_scene_registry_rule_1_scenes.py`

### ผลกระทบที่ full-suite run จับได้ (ตามแบบรอบ p7wm17)

การเปิดฉาก 7 ทำให้ `world_faction_admission.admits(7)` เป็น True ซึ่งกระทบ `player_wire`'s scene guard
ด้วย — สองไฟล์ที่ hardcode ฉาก 7 เป็นตัวอย่าง "refused/unaccepted scene" (ที่รอบ `p7wm17` เพิ่งย้ายมาจาก
ฉาก 3) พังตอนรัน full suite และถูกย้ายไปฉาก 9 (Death City Sea, ยังปิดอยู่) แทน: `tests/test_player_hostile_pairing.py`,
`tests/test_player_wire_probe_base1.py` เช่นเดียวกับ `NAMED_BUT_UNPINNED` ใน
`test_gm_login_scene_admission.py`, `BARRED_ON_DISK` ใน `test_gm_login_scene_registry_snapshot.py`,
`SHUT_AT_LOGIN` ใน `test_world_faction_admission.py` และตัวอย่าง scene-7 ใน
`test_gm_login_scene_consume_cause.py` ที่ต้องย้ายจากฉาก 7 ไปฉาก 9 ด้วยเหตุผลเดียวกัน

### สิ่งที่พบเพิ่ม นอกขอบเขตที่คาดไว้แต่ต้องแก้ให้ green: numeric false-positive ใน tripwire คนละสาย

`tests/test_presentation_ownership.py::MusicControlOwnershipTests` มี regex `16047` (MusicControlVital
0x3EAF = 16047 decimal) ที่ชนกับ **พิกัดจริง** ของ placement 25 ในฉาก 7 (y=16047.994140625, ตรวจแล้วตรงกับ
`gamedata/scene/Bg0007/Bg0007.placements.tsv` row index 25) — ไม่ใช่การพูดถึง MusicControlVital จริง
แก้ regex ให้แคบลงด้วย negative lookahead `(?!\.\d)` (ไม่กระทบการจับ spelling อื่นเลย) แทนที่จะแก้ข้อมูล
พิกัดจริงเพื่อหลบเทส — co-maintenance edit บนไฟล์นอกเขตเขียนของสาย A เหมือนที่ทำกับ `mob_scene_recompose.py`
รอบ p7wm17: ข้อเท็จจริงที่ตรวจสอบได้อิสระ (ตัวเลขพิกัดตรงกับ source TSV) ไม่ใช่การตัดสินใจของสาย A

## ตัวเลขที่วัดได้

- assembled 56 shippable placements / 68 native placements (12 unshippable: 2 no-MOBS-row
  รวม set 111 ที่ leader n_ID เป็นศูนย์ + 10 no-s_OUTFIT)
- 44 resolved Mob-Set identities / 12 unresolved / 56 total (CLINE type 7's ทั้งช่วง key)
- 8 multi-variant outfit sets (ทุกตัวสองตัวแปร), ครอบคลุม 18 ของ 56 shippable placements
- full suite ก่อน commit: **5968 passed, 327 skipped, 12385 subtests passed, 0 failed**
  (เทียบกับ 5967/327/12384 ก่อนรอบนี้ [หลังรอบ jqxe6v] — เพิ่ม test methods ใหม่จากไฟล์ที่เพิ่ม/แก้ทั้งหมด)

## ยังไม่ได้พิสูจน์

- ไม่มีมนุษย์ยืนในฉากนี้มาก่อนในโปรเจกต์นี้ (`status` เดิม: `never_sent_to_any_client_by_this_project`)
  จุดเกิด `MARKER[7]` ยังเป็นชั้นหลักฐาน `authored` เท่านั้น แม้จะอยู่ในขอบเขต placement และห่างแค่ 10.793
  หน่วย (geometry แน่นที่สุดที่ lane นี้เคยเปิด) — ต้องรอ attended round ยืนดูจริง
- ticket สาย C: เปิด GT-176 ใหม่ใน `pf_bridge/GAME_TEST_QUEUE.md` (ดูจดหมายแยก)

## งานอื่นที่ทำรอบนี้ (นอกเหนือจาก build หลัก)

- ยืนยันรับข้อเสนอร่วมของ LANE-B (สาย B) สำหรับ scene-14 hostile splice และส่ง CORE-REQUEST ร่วมให้ chief
  เปิดกิ่ง `runtime.py:7501` (ทั้งสองสายสร้างครึ่งของตัวเองไว้แล้วก่อนรอบนี้ เหลือแค่จุดเสียบ) — ดูจดหมาย
  `pf_bridge/notes_to_chief/20260831_2151_LANE-A-TO-CHIEF-scene14-hostile-splice-core-request-both-
  halves-confirmed-built.md`
- ตามงานค้างของรอบก่อน: ย้ายใบจอง CLAIM ของรอบ `p7wm17` และ `p4wire` เข้า `consumed/` พร้อม stub
  (งานเสร็จและ merge แล้วแต่ไม่มีใครย้ายใบจองตอนจบรอบเดิม)

## ขอบเขตที่ไม่แตะ

`runtime.py`, `app.py`, `current/pf_login_game_server_v141.py` — ไม่แตะเลย

## CORE-REQUEST

`runtime.py:7501` -- เปิดกิ่งให้ฉาก 14 เรียก `world_population_bg0015.build_bg0015_population(...)` แล้ว
ส่งต่อให้ `mob_scene_recompose.splice_identity_override(legacy, generation,
field_mob_hostile_bg0015.scene14_hostile_overrides(legacy))` ครั้งเดียว (ทั้งสองสายยืนยันแล้ว รายละเอียด
เต็มในจดหมายแยก)
